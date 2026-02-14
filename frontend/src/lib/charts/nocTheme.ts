import * as echarts from "echarts";

export const NOC_THEME_NAME = "noc-dark";

let themeRegistered = false;

export function registerNocTheme() {
  if (themeRegistered) return;
  echarts.registerTheme(NOC_THEME_NAME, {
    backgroundColor: "transparent",
    textStyle: { color: "#9ca3af" },
    title: { textStyle: { color: "#e5e7eb" } },
    legend: { textStyle: { color: "#9ca3af" } },
    tooltip: {
      backgroundColor: "#1f2937",
      borderColor: "#374151",
      textStyle: { color: "#f3f4f6" },
    },
    line: { itemStyle: { borderWidth: 2 } },
    categoryAxis: {
      axisLine: { lineStyle: { color: "#374151" } },
      axisTick: { lineStyle: { color: "#374151" } },
      axisLabel: { color: "#6b7280" },
      splitLine: { lineStyle: { color: "#1f2937" } },
    },
    valueAxis: {
      axisLine: { lineStyle: { color: "#374151" } },
      axisLabel: { color: "#6b7280" },
      splitLine: { lineStyle: { color: "#1f2937", type: "dashed" } },
    },
  });
  themeRegistered = true;
}
