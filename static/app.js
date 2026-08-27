let trendChart;
let regionChart;
const money = value => new Intl.NumberFormat("en-IN", {style:"currency", currency:"INR", maximumFractionDigits:0}).format(value);
const number = value => new Intl.NumberFormat("en-IN").format(value);
const changeText = value => `${value >= 0 ? "+" : ""}${value}% vs previous month`;

document.getElementById("uploadForm").addEventListener("submit", async event => {
  event.preventDefault();
  const message = document.getElementById("message");
  message.style.color = "#2563eb";
  message.textContent = "Analyzing your files...";
  try {
    const response = await fetch("/api/analyze", {method:"POST", body:new FormData(event.target)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Analysis failed.");
    renderDashboard(data);
    message.style.color = "#0f9f8f";
    message.textContent = "Analysis completed successfully.";
  } catch (error) {
    message.style.color = "#dc2626";
    message.textContent = error.message;
  }
});

function renderDashboard(data) {
  document.getElementById("dashboard").classList.remove("hidden");
  document.getElementById("revenue").textContent = money(data.kpis.total_revenue);
  document.getElementById("profit").textContent = money(data.kpis.total_profit);
  document.getElementById("margin").textContent = `${data.kpis.profit_margin}%`;
  document.getElementById("orders").textContent = number(data.kpis.total_orders);
  document.getElementById("revenueChange").textContent = changeText(data.comparison.revenue_change);
  document.getElementById("profitChange").textContent = changeText(data.comparison.profit_change);
  document.getElementById("ordersChange").textContent = changeText(data.comparison.orders_change);
  document.getElementById("summary").textContent = data.executive_summary;
  document.getElementById("rating").textContent = `${data.feedback.average_rating}/5`;
  document.getElementById("feedbackTotal").textContent = `${data.feedback.total} responses`;
  document.getElementById("aiStatus").textContent = data.ai_enabled ? "Gemini AI connected" : "Local analysis mode";
  document.getElementById("sentiments").innerHTML = Object.entries(data.feedback.sentiment).map(([key,value]) => `<span>${key}: <b>${value}</b></span>`).join("");
  document.getElementById("themes").innerHTML = data.feedback.themes.map(item => `<span>${item.name} · ${item.count}</span>`).join("");
  document.getElementById("risks").innerHTML = data.risks.map(item => `<li>${item}</li>`).join("");
  document.getElementById("opportunities").innerHTML = data.opportunities.map(item => `<li>${item}</li>`).join("");

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(document.getElementById("trendChart"), {type:"line", data:{labels:data.monthly.map(x=>x.Month), datasets:[{label:"Revenue",data:data.monthly.map(x=>x.Revenue),borderColor:"#2563eb",backgroundColor:"rgba(37,99,235,.08)",fill:true,tension:.35},{label:"Profit",data:data.monthly.map(x=>x.Profit),borderColor:"#0f9f8f",tension:.35}]}, options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:"bottom"}},scales:{x:{grid:{display:false}},y:{ticks:{callback:v=>"₹"+(v/100000).toFixed(1)+"L"}}}}});
  if (regionChart) regionChart.destroy();
  regionChart = new Chart(document.getElementById("regionChart"), {type:"bar",data:{labels:data.regions.map(x=>x.Region),datasets:[{label:"Revenue",data:data.regions.map(x=>x.Revenue),backgroundColor:["#2563eb","#0f9f8f","#8b5cf6","#f59e0b"],borderRadius:7}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false}},y:{ticks:{callback:v=>"₹"+(v/100000).toFixed(0)+"L"}}}}});
  document.getElementById("dashboard").scrollIntoView({behavior:"smooth"});
}

document.getElementById("scenarioForm").addEventListener("submit", async event => {
  event.preventDefault();
  const result = document.getElementById("scenarioResult");
  const response = await fetch("/api/scenario", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({revenue_growth:Number(document.getElementById("revenueGrowth").value),cost_growth:Number(document.getElementById("costGrowth").value)})});
  const data = await response.json();
  if (!response.ok) return result.textContent = data.detail;
  result.innerHTML = `<b>Projected revenue:</b> ${money(data.projected_revenue)}<br><b>Projected profit:</b> ${money(data.projected_profit)}<br><b>Profit change:</b> ${data.profit_change}%`;
});

document.getElementById("chatForm").addEventListener("submit", async event => {
  event.preventDefault();
  const box = document.getElementById("chatBox");
  box.textContent = "Thinking...";
  const response = await fetch("/api/chat", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:document.getElementById("question").value})});
  const data = await response.json();
  box.textContent = data.answer || data.detail;
});
