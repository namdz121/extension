export interface AllowedModel {
  id: string;
  name: string;
  desc?: string;
}

export interface SettingsDTO {
  gemini_api_key: string;
  tavily_api_key: string;
  gemini_model: string;
}

export interface SettingsResponseDTO {
  gemini_api_key: string;
  tavily_api_key: string;
  gemini_model: string;
  has_gemini_key: boolean;
  has_tavily_key: boolean;
  env_file_path: string;
  allowed_models: AllowedModel[];
}

export interface TestKeyRequestDTO {
  service: 'gemini' | 'tavily';
  api_key: string;
  gemini_model?: string;
}

export interface TestKeyResponseDTO {
  success: boolean;
  message: string;
}

export interface SaveSettingsResponseDTO {
  status: string;
  message: string;
  settings: {
    gemini_api_key: string;
    tavily_api_key: string;
    gemini_model: string;
  };
}
