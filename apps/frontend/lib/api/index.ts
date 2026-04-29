/**
 * API Module Exports
 *
 * Centralized exports for all API-related functionality.
 */

// Client utilities
export {
    API_BASE, API_URL, apiDelete, apiFetch, apiPatch, apiPost, apiPut, getUploadUrl
} from './client';

// Resume operations
export {
    confirmImproveResume, deleteResume, downloadResumePdf, fetchResume,
    fetchResumeList, improveResume,
    previewImproveResume, updateResume, uploadJobDescriptions, type ResumeListItem
} from './resume';

// Config operations
export {
    fetchLlmApiKey, fetchLlmConfig, fetchPromptConfig, fetchSystemStatus,
    PROVIDER_INFO, testLlmConnection, updateLlmApiKey, updateLlmConfig, updatePromptConfig, type DatabaseStats, type LLMConfig,
    type LLMConfigUpdate, type LLMHealthCheck, type LLMProvider, type PromptConfig,
    type PromptConfigUpdate, type PromptOption, type SystemStatus
} from './config';

