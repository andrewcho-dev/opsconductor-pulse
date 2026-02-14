export type DeviceDetailsData = {
  name: string;
  device_type: string;
  site_id?: string;
};

export type TagsGroupsData = {
  tags: string[];
  group_ids: string[];
};

export type CombinedWizardData = DeviceDetailsData & TagsGroupsData;

export type ProvisionResult = {
  device_id: string;
  client_id: string;
  password: string;
  broker_url: string;
};
