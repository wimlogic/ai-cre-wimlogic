import { AppConfig } from '../config/app';

class ApiClient {
  private getBaseUrl(): string {
    const url = AppConfig.apiBaseUrl;
    if (!url) {
      return 'http://127.0.0.1:8000/api/v1';
    }
    return url;
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const baseUrl = this.getBaseUrl();
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${baseUrl}${cleanEndpoint}`;

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        let errorDetail = '';
        try {
          const errJson = await response.json();
          errorDetail = errJson.detail || JSON.stringify(errJson);
        } catch {
          errorDetail = await response.text();
        }
        throw new Error(errorDetail || `HTTP error! status: ${response.status}`);
      }
      return await response.json() as T;
    } catch (error: any) {
      console.error(`API Client Error [${options.method || 'GET'} ${url}]:`, error);
      throw error;
    }
  }

  get<T>(endpoint: string, options?: Omit<RequestInit, 'method'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  post<T>(endpoint: string, body: any, options?: Omit<RequestInit, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  put<T>(endpoint: string, body: any, options?: Omit<RequestInit, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(body),
    });
  }

  delete<T>(endpoint: string, options?: Omit<RequestInit, 'method'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }

  /**
   * Multipart/form-data upload.
   *
   * Deliberately bypasses `request()`'s JSON handling: FormData must be sent
   * with a browser-generated `Content-Type: multipart/form-data; boundary=...`
   * header, so we must NOT set Content-Type ourselves here.
   */
  async upload<T>(
    endpoint: string,
    formData: FormData,
    options?: Omit<RequestInit, 'method' | 'body' | 'headers'>
  ): Promise<T> {
    const baseUrl = this.getBaseUrl();
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${baseUrl}${cleanEndpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        let errorDetail = '';
        try {
          const errJson = await response.json();
          errorDetail = errJson.detail || JSON.stringify(errJson);
        } catch {
          errorDetail = await response.text();
        }
        throw new Error(errorDetail || `HTTP error! status: ${response.status}`);
      }
      return await response.json() as T;
    } catch (error: any) {
      console.error(`API Client Error [UPLOAD ${url}]:`, error);
      throw error;
    }
  }
}

export const apiClient = new ApiClient();
