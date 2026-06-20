export interface Document {
  id: string;
  filename: string;
  original_filename?: string;
  file_type: string;
  session_id: string;
  chunk_count: number;
  file_size: number;
  is_excel: boolean;
  uploaded_at: string;
  status: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: { filename: string; text: string; score: number }[];
  created_at?: string;
  timestamp?: string;
  action?: string;
  payload?: any;
  download_id?: string;
  dataset_download_id?: string;
  is_docx_edit?: boolean;
  isStreaming?: boolean;
}

export type Message = ChatMessage;

export interface Source {
  filename: string;
  text: string;
  score: number;
}

// --- NEW DATASET TYPES ---

export interface Dataset {
  dataset_id: string;
  document_id?: string;
  source_type: "CSV" | "MYSQL";
  connection_details?: any;
  schema_snapshot: any;
  row_count: number;
  display_name: string;
  version: number;
  created_at: string;
  updated_at: string;
  status: string;
}

export interface Mutation {
  mutation_id: string;
  dataset_id: string;
  version: number;
  operation_type: string;
  description: string;
  rows_affected: number;
  success: boolean;
  error_message?: string;
  executed_at: string;
  reversible: boolean;
}

export interface IntentResult {
  intent: string;
  confidence: number;
  explanation: string;
}