export const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://api.strumind.com' 
  : 'https://work-1-tgaufxkwcjeifuoc.prod-runtime.all-hands.dev'

export const API_ENDPOINTS = {
  auth: {
    login: `${API_BASE_URL}/api/v1/auth/login`,
    register: `${API_BASE_URL}/api/v1/auth/register`,
    me: `${API_BASE_URL}/api/v1/auth/me`,
  },
  projects: {
    list: `${API_BASE_URL}/api/v1/projects/`,
    create: `${API_BASE_URL}/api/v1/projects/`,
    get: (id: string) => `${API_BASE_URL}/api/v1/projects/${id}`,
  },
}