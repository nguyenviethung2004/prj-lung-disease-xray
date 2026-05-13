
const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

export async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || "Đăng nhập thất bại");
  }

  // Save tokens to localStorage
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  localStorage.setItem("user", JSON.stringify(data.user));

  return data;
}

export async function changePassword(oldPassword: string, newPassword: string) {
  const data = await apiFetch("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });

  // Update tokens and user info in localStorage from the new response
  if (data.access_token && data.refresh_token) {
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
  }
  
  if (data.user) {
    localStorage.setItem("user", JSON.stringify(data.user));
  } else {
    // Fallback (nên ưu tiên data.user từ server)
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    user.must_change_password = false;
    localStorage.setItem("user", JSON.stringify(user));
  }

  return data;
}

export async function logout() {
  const token = localStorage.getItem("access_token");
  if (token) {
    try {
      await fetch(`${API_BASE_URL}/auth/logout-token`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
    } catch (error) {
      console.error("Lỗi khi gọi API logout:", error);
    }
  }

  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
}

export function getAuthUser() {
  if (typeof window === "undefined") return null;
  const user = localStorage.getItem("user");
  return user ? JSON.parse(user) : null;
}

export async function refreshToken() {
  const refresh_token = localStorage.getItem("refresh_token");
  if (!refresh_token) {
    await logout();
    throw new Error("No refresh token available");
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${refresh_token}`
      }
    });

    const data = await response.json();

    if (!response.ok) {
      await logout();
      throw new Error(data.message || "Refresh token expired or invalid");
    }

    localStorage.setItem("access_token", data.access_token);
    return data.access_token;
  } catch (error) {
    await logout();
    throw error;
  }
}

export async function getAllUsers(role?: string) {
  let url = `/auth/admin/users`;
  if (role && role !== "All") {
    url += `?role=${role}`;
  }
  return await apiFetch(url, { method: "GET" });
}

export async function adminCreateUser(email: string, username: string, role: string) {
  return await apiFetch("/auth/admin/create-user", {
    method: "POST",
    body: JSON.stringify({ email, username, role }),
  });
}

export async function adminDeleteUser(userId: number) {
  return await apiFetch(`/auth/admin/delete-user/${userId}`, {
    method: "DELETE",
  });
}

export async function adminUpdateUser(userId: number, updateData: any) {
  return await apiFetch(`/auth/admin/update-user/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(updateData),
  });
}

/**
 * Centered API Fetch wrapper with auto token refresh logic
 */
export async function apiFetch(path: string, options: any = {}) {
  const token = localStorage.getItem("access_token");
  
  const headers: any = {
    ...options.headers,
  };

  // Only set application/json if body is not FormData
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  let response = await fetch(url, { ...options, headers });

  // Auto-refresh token if 401 Unauthorized occurs with "Token expired" message
  if (response.status === 401) {
    try {
      const clonedResponse = response.clone();
      const body = await clonedResponse.json();
      
      if (body.message === "Token expired") {
        const newToken = await refreshToken();
        // Update headers and retry the search
        headers["Authorization"] = `Bearer ${newToken}`;
        response = await fetch(url, { ...options, headers });
      }
    } catch (err) {
      // Body might not be JSON, skip refresh logic
    }
  }

  // Handle empty responses (like 204 No Content)
  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(data?.message || "Yêu cầu thất bại");
  }
  return data;
}
