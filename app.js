const API_BASE = "http://127.0.0.1:5000/api";

async function sendRequest(endpoint, method = "GET", body = null) {
  const options = {
    method,
    headers: {
      "Content-Type": "application/json"
    }
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    console.error("Network Error:", err);
    return { ok: false, status: 500, data: { message: "Server connection failed! Please ensure Flask backend is running on port 5000." } };
  }
}

function enforceSession(role, redirectUrl) {
  const sessionKey = `gpm_${role}`;
  const user = JSON.parse(sessionStorage.getItem(sessionKey) || sessionStorage.getItem('gpm_academic_staff') || "null");
  if (!user) {
    window.location.href = redirectUrl;
    return null;
  }
  return user;
}

function terminateSession(role, redirectUrl) {
  sessionStorage.removeItem(`gpm_${role}`);
  sessionStorage.removeItem('gpm_academic_staff');
  window.location.href = redirectUrl;
}