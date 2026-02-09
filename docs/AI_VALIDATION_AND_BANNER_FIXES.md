# AI Validation & Network Degraded Banner Fixes

**Date:** 2026-02-10
**Commit:** 98c1bac
**Status:** ✅ Deployed to dcloud (root@198.18.134.22)

## Problem Statement

Two related issues were identified in the pipeline:

### Issue 1: AI Validation Returns Incomplete Data
- Missing `overall_score` field (required for UI display)
- Missing `rollback_recommended` boolean (breaks rollback banner logic)
- Missing `rollback_reason` string (needed for operator context)
- Malformed `findings` array showing as colons `:` in UI
- Only partial findings displayed instead of structured data

**Root Cause:**
LLM responses in real mode were not guaranteed to return all required fields. The JSON parsing logic accepted whatever the LLM returned without validation, leading to incomplete data structures.

### Issue 2: No Network Degraded Banner
- Network degradation only visible when clicking monitoring stage
- No immediate visual warning when `deployment_healthy = false`
- Rollback button buried in modal instead of prominent
- Operators had to actively search for the issue instead of seeing it immediately

**Root Cause:**
Missing UI component to display monitoring stage results. The "Rollback Required" banner only triggered on AI validation, not monitoring stage results.

## Solution Overview

### Part 1: Backend - AI Validation Hardening

**File:** `backend/services/llm_service.py`

**Changes:**

1. **Enhanced LLM System Prompt (lines 614-654)**
   - Added explicit JSON structure requirements
   - Listed all required fields with expected types
   - Specified critical rules for rollback decisions
   - Required at least 3 findings with 4 fields each

2. **Response Validation (lines 662-756)**
   ```python
   # Validate all required fields exist
   required_fields = {
       'validation_status': str,
       'overall_score': (int, float),
       'rollback_recommended': bool,
       'findings': list,
       'summary': str,
       'recommendation': str,
   }
   ```
   - Checks each field exists and has correct type
   - Adds default values if fields are missing
   - Converts types if mismatched
   - Validates findings array structure
   - Generates `rollback_reason` if missing
   - Logs warnings for any corrections made

3. **Fallback Method (lines 758-779)**
   ```python
   def _fallback_validation(self, monitoring_diff):
       """Generate fallback validation when LLM response fails to parse."""
       deployment_healthy = monitoring_diff.get('deployment_healthy', True)
       return {
           'validation_status': 'FAILED' if not deployment_healthy else 'PASSED',
           'overall_score': 30 if not deployment_healthy else 90,
           'rollback_recommended': not deployment_healthy,
           'rollback_reason': 'Network degraded - automatic assessment...',
           'findings': [...],
           'summary': 'Automated validation due to LLM error',
           'recommendation': '...'
       }
   ```
   - Used when LLM response completely fails to parse
   - Uses monitoring diff to determine health
   - Returns fully structured validation data
   - Ensures pipeline never blocks on LLM errors

**Result:**
AI validation now always returns complete, properly structured data with all required fields, regardless of LLM response quality.

### Part 2: Frontend - Network Degraded Banner

**File:** `frontend/src/components/Pipeline.tsx`

**Changes:**

Added new banner component after line 175 (between "Rollback Required" and "Pipeline Progress"):

```tsx
{/* Network Degraded Banner */}
{(() => {
  const monitoring = stagesData.monitoring?.data;
  const isNetworkDegraded =
    stagesData.monitoring?.status === 'completed' &&
    monitoring?.deployment_healthy === false;

  if (!isNetworkDegraded) return null;

  // Build message about what degraded
  const degradedMetrics: string[] = [];
  if (monitoring.diff) {
    Object.entries(monitoring.diff).forEach(([metric, values]: [string, any]) => {
      if (values.change < 0) {
        degradedMetrics.push(
          `${metric.replace(/_/g, ' ')}: ${values.before} → ${values.after} (${values.change})`
        );
      }
    });
  }

  const message = degradedMetrics.length > 0
    ? `Network state degraded: ${degradedMetrics.join(', ')}`
    : 'Network state degraded after deployment';

  return (
    <div className="mb-4">
      <AlertBanner
        severity="critical"
        title="🔴 NETWORK DEGRADED"
        message={message}
        onAction={handleRollbackClick}
        actionLabel={isRollingBack ? 'Rolling back...' : 'Execute Rollback'}
      />
    </div>
  );
})()}
```

**Banner Logic:**
1. Triggers when monitoring stage completes with `deployment_healthy === false`
2. Dynamically builds message from `monitoring.diff` data
3. Shows which metrics degraded (OSPF neighbors, routes, interfaces)
4. Includes "Execute Rollback" button
5. Uses existing `handleRollbackClick` handler

**Example Messages:**

```
Network state degraded: ospf neighbors: 3 → 0 (-3), routes: 6 → 0 (-6)
Network state degraded: interfaces up: 5 → 3 (-2)
Network state degraded: ospf neighbors: 2 → 1 (-1), routes: 24 → 10 (-14)
```

**Result:**
Immediate, prominent visual warning when monitoring detects network degradation. Appears after Stage 8 completes, before AI validation runs.

## Banner Hierarchy

After both fixes, three alert banners can display:

1. **"PIPELINE FAILED"** (Line 103-118)
   - Triggers: Any stage status === 'failed'
   - Highest priority

2. **"NETWORK DEGRADED"** (Line 176-202, NEW)
   - Triggers: Monitoring stage `deployment_healthy === false`
   - High priority
   - Appears immediately after Stage 8 completes

3. **"ROLLBACK REQUIRED"** (Line 120-175)
   - Triggers: AI validation `rollback_recommended === true` OR `validation_status === 'FAILED'`
   - Important priority
   - Appears after Stage 10 completes
   - Often redundant with #2 but provides AI confirmation

**Timeline:**
```
Stage 8 (Monitoring) completes with deployment_healthy=false
  → "NETWORK DEGRADED" banner appears ✓

Stage 10 (AI Validation) completes with rollback_recommended=true
  → "ROLLBACK REQUIRED" banner ALSO appears ✓

Both banners visible, providing immediate warning + AI confirmation
```

## Expected User Experience

### Before Fixes
❌ Network degrades → No visible warning
❌ AI validation incomplete → No rollback banner
❌ Engineer must click monitoring stage to see issue
❌ Rollback button buried in modal

### After Both Fixes
✅ Network degrades → "NETWORK DEGRADED" banner appears immediately (Stage 8)
✅ AI validation completes with full data (Stage 10)
✅ "ROLLBACK REQUIRED" banner also appears
✅ Two banners provide redundant warning = safer
✅ Both have "Execute Rollback" buttons
✅ Clear visual hierarchy

## Verification Steps

### Backend Verification

1. **Check AI Validation Data Structure:**
   ```bash
   # Run operation that causes network degradation
   # After AI validation completes, inspect stage data:
   curl http://198.18.134.22:8003/api/v1/operations/{id}
   ```

   Verify response contains:
   ```json
   {
     "ai_validation": {
       "status": "completed",
       "data": {
         "validation_status": "PASSED|WARNING|FAILED",
         "overall_score": 75,
         "rollback_recommended": true,
         "rollback_reason": "Network degradation detected...",
         "findings": [
           {
             "category": "OSPF Neighbors",
             "status": "error",
             "severity": "critical",
             "message": "CRITICAL: OSPF neighbor count decreased (-3)"
           }
         ],
         "summary": "...",
         "recommendation": "..."
       }
     }
   }
   ```

2. **Check Backend Logs:**
   ```bash
   ssh root@198.18.134.22 'docker logs brkops-backend | grep -A5 "validation"'
   ```

   Should NOT see:
   - "Missing required field" errors
   - JSON parsing failures
   - Incomplete data structures

3. **Test Rollback Banner:**
   - If `rollback_recommended=true`, verify banner appears
   - Click "Initiate Rollback" to test functionality

### Frontend Verification

1. **Trigger Network Degradation:**
   - Navigate to demo page
   - Execute operation that causes network degradation
   - Or use browser DevTools to modify state

2. **Verify Banner Appearance:**
   - After monitoring stage completes
   - Banner should appear immediately above pipeline stages
   - Should display "🔴 NETWORK DEGRADED" title
   - Should show detailed degradation message

3. **Test Rollback Button:**
   - Click "Execute Rollback" button
   - Button should show "Rolling back..." during execution
   - Should call `/api/v1/operations/{id}/rollback` endpoint
   - Should refresh operation data after completion

4. **Test Multiple Banners:**
   - Verify multiple banners can display simultaneously
   - Verify banner order:
     1. Pipeline Failed
     2. Network Degraded
     3. Rollback Required

## Edge Cases Handled

### Backend
1. **LLM returns invalid JSON:**
   - Regex extraction attempted
   - Falls back to `_fallback_validation()`
   - Uses monitoring diff for health assessment

2. **LLM returns incomplete JSON:**
   - Each field validated individually
   - Missing fields filled with defaults
   - Warnings logged for debugging

3. **LLM returns wrong types:**
   - Type conversion attempted
   - Falls back to safe defaults
   - Ensures pipeline continues

4. **No monitoring diff available:**
   - Assumes deployment healthy
   - Returns PASSED validation

### Frontend
1. **Multiple degradation metrics:**
   - Message concatenates all negative changes
   - Keeps message readable

2. **No diff data:**
   - Falls back to generic message:
     "Network state degraded after deployment"

3. **Monitoring stage not complete:**
   - Banner does not appear
   - Only shows after monitoring completes

4. **Both banners active:**
   - Both display (independent conditions)
   - Network Degraded appears first (closer to top)

5. **Rollback in progress:**
   - Button shows "Rolling back..."
   - Button disabled during rollback

## Risk Assessment

**Low Risk Change:**
- ✅ Only adds UI display logic (frontend)
- ✅ Only adds validation logic (backend)
- ✅ Uses existing AlertBanner component
- ✅ Uses existing rollback handler
- ✅ No changes to data structures or API contracts

**No Breaking Changes:**
- ✅ Existing functionality unchanged
- ✅ Additional banner, doesn't replace anything
- ✅ Follows same pattern as existing banners
- ✅ Backwards compatible with existing data

## Deployment

```bash
# 1. Rsync code (excluding .env files)
rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' \
  --exclude '.env' --exclude '.env.dcloud' --exclude 'venv' --exclude '.next' \
  --exclude 'dist' --exclude 'build' --delete \
  /Users/cbeye/AI/brkops-2585/ root@198.18.134.22:/opt/brkops-2585/

# 2. Rebuild containers
ssh root@198.18.134.22 'cd /opt/brkops-2585 && docker compose build --no-cache backend frontend'

# 3. Restart services
ssh root@198.18.134.22 'cd /opt/brkops-2585 && docker compose up -d'

# 4. Clean up old images
ssh root@198.18.134.22 'docker image prune -f'
```

**Deployment Status:** ✅ Completed 2026-02-10

## Files Modified

1. `backend/services/llm_service.py`
   - Lines 614-654: Enhanced system prompt
   - Lines 662-756: Response validation logic
   - Lines 758-779: Fallback validation method

2. `frontend/src/components/Pipeline.tsx`
   - Lines 176-202: Network degraded banner component

## Testing Recommendations

1. **Test with Real LLM:**
   - Set `DEMO_MODE=false`
   - Execute operations that cause network degradation
   - Verify complete validation data returned

2. **Test with Demo Mode:**
   - Set `DEMO_MODE=true`
   - Verify demo validation still works
   - Compare structure with real LLM output

3. **Test Network Degraded Banner:**
   - Trigger OSPF neighbor loss
   - Trigger interface down
   - Trigger route loss
   - Verify banner message accuracy

4. **Test Rollback Flow:**
   - Click "Execute Rollback" from Network Degraded banner
   - Click "Initiate Rollback" from Rollback Required banner
   - Verify both trigger same rollback logic

5. **Test Error Scenarios:**
   - LLM returns malformed JSON
   - LLM returns partial fields
   - Monitoring diff missing
   - Multiple simultaneous banners

## Future Improvements

1. **Enhanced LLM Prompting:**
   - Use function calling for guaranteed structure
   - Add examples to prompt for better consistency

2. **Banner Customization:**
   - Allow banner message length limit
   - Add collapse/expand for long messages
   - Add metric-specific icons

3. **Rollback Automation:**
   - Auto-rollback option based on severity
   - Configurable rollback rules
   - Rollback preview before execution

4. **Monitoring Integration:**
   - Real-time network state updates in banner
   - Link to monitoring dashboard
   - Historical degradation comparison

## Related Documentation

- [Pipeline Architecture](./PLATFORM_DESIGN_DOCUMENT.md)
- [LLM Service Documentation](../backend/services/README.md)
- [Alert Banner Component](../frontend/src/components/AlertBanner.tsx)
- [Monitoring Stage](../backend/stages/monitoring.py)

## Support

For issues or questions:
- Check backend logs: `docker logs brkops-backend`
- Check frontend logs: `docker logs brkops-frontend`
- Review operation data: `GET /api/v1/operations/{id}`
- Inspect browser console for frontend errors
