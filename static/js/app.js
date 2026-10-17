/**
 * LabCare Global Application & Service Interceptor
 */

function handleServiceSelection(activityId, serviceName, activityPrice) {
  const isAuthenticated = document.body.dataset.authenticated === "true";

  if (!isAuthenticated) {
    // Open the Auth Gate Modal on the homepage
    openAuthGateModal(activityId, serviceName, activityPrice);
  } else {
    // Authenticated dispatch: route directly to client dashboard
    window.location.href = `/dashboard/?action=order&activity_id=${activityId}`;
  }
}

function openAuthGateModal(activityId, serviceName, activityPrice) {
  const modal = document.getElementById("auth-gate-modal");
  if (!modal) {
    // Fallback if modal container isn't rendered
    window.location.href = `/auth/?mode=register&role=client&redirect_activity=${activityId}`;
    return;
  }

  // Populate selected service details
  document.getElementById("modal-activity-name").textContent = serviceName;
  document.getElementById("modal-activity-price").textContent = `Ksh${activityPrice}`;
  
  // Set dynamic action buttons
  document.getElementById("modal-btn-login").href = `/auth/?mode=login&role=client&redirect_activity=${activityId}`;
  document.getElementById("modal-btn-register").href = `/auth/?mode=register&role=client&redirect_activity=${activityId}`;

  modal.style.display = "flex";
}

function closeAuthGateModal() {
  const modal = document.getElementById("auth-gate-modal");
  if (modal) modal.style.display = "none";
}

async function performDownloadReport(orderId) {
  try {
    const response = await fetch(`/api/v1/orders/${orderId}/download-report/`, {
      method: "GET"
    });
    
    if (response.status === 404) {
      alert("Validation hold: Laboratory report is still in analysis or being compiled.");
      return;
    }
    
    if (!response.ok) {
      alert("Access authorization error: Cannot access cross-profile clinical documents.");
      return;
    }
    
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `Prswim_Report_${orderId}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (err) {
    alert("Network connection failed during document retrieval.");
  }
}

