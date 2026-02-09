-- Add OSPF configuration strategy field to use_cases table
-- This enables flexible OSPF command generation: dual (network + interface), network_only, or interface_only

ALTER TABLE use_cases ADD COLUMN IF NOT EXISTS ospf_config_strategy VARCHAR(20) DEFAULT 'dual';

-- Update existing OSPF use case to use dual mode (default)
UPDATE use_cases SET ospf_config_strategy = 'dual' WHERE name = 'ospf_configuration_change';

-- Add comment for documentation
COMMENT ON COLUMN use_cases.ospf_config_strategy IS 'OSPF config generation mode: dual (network statements + interface commands), network_only (legacy), interface_only (modern)';
