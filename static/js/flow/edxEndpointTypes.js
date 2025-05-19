export type EdxEndpoint = {
  id: number,
  name: string,
  base_url: string,
  edx_video_api_path: string,
  is_global_default: boolean,
  created_at: string,
  updated_at: string,
};

export type EdxEndpointList = Array<EdxEndpoint>;
