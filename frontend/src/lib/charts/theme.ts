import * as echarts from "echarts";
import { CHART_COLORS } from "./colors";

/** ECharts theme name — use this when initializing charts */
export const ECHARTS_THEME = "pulse-dark";

/**
 * Register the Pulse dark theme with ECharts.
 * Call this once at app startup.
 */
export function registerPulseDarkTheme(): void {
  echarts.registerTheme(ECHARTS_THEME, {
    color: [...CHART_COLORS],
    backgroundColor: "transparent",
    textStyle: {
      color: "#a1a1aa", // zinc-400
    },
    title: {
      textStyle: { color: "#fafafa" },
      subtextStyle: { color: "#a1a1aa" },
    },
    gauge: {
      axisLine: {
        lineStyle: {
          color: [[1, "#27272a"]], // zinc-800
        },
      },
      axisTick: { lineStyle: { color: "#52525b" } },
      splitLine: { lineStyle: { color: "#52525b" } },
      axisLabel: { color: "#a1a1aa" },
      detail: {
        color: "#fafafa",
      },
      title: {
        color: "#a1a1aa",
      },
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: "#3f3f46" } },
      axisTick: { lineStyle: { color: "#3f3f46" } },
      axisLabel: { color: "#a1a1aa" },
      splitLine: { lineStyle: { color: "#27272a" } },
    },
    valueAxis: {
      axisLine: { lineStyle: { color: "#3f3f46" } },
      axisTick: { lineStyle: { color: "#3f3f46" } },
      axisLabel: { color: "#a1a1aa" },
      splitLine: { lineStyle: { color: "#27272a" } },
    },
    legend: {
      textStyle: { color: "#a1a1aa" },
    },
    tooltip: {
      backgroundColor: "#18181b",
      borderColor: "#3f3f46",
      textStyle: { color: "#fafafa" },
    },
  });
}
