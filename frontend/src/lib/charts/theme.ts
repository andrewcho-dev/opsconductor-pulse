import * as echarts from "echarts";
import { CHART_COLORS } from "./colors";

export const ECHARTS_DARK_THEME = "pulse-dark";
export const ECHARTS_LIGHT_THEME = "pulse-light";

export function registerPulseThemes(): void {
  echarts.registerTheme(ECHARTS_DARK_THEME, {
    color: [...CHART_COLORS],
    backgroundColor: "transparent",
    textStyle: {
      color: "#a1a1aa",
    },
    title: {
      textStyle: { color: "#fafafa" },
      subtextStyle: { color: "#a1a1aa" },
    },
    gauge: {
      axisLine: {
        lineStyle: {
          color: [[1, "#27272a"]],
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

  echarts.registerTheme(ECHARTS_LIGHT_THEME, {
    color: [...CHART_COLORS],
    backgroundColor: "transparent",
    textStyle: {
      color: "#52525b",
    },
    title: {
      textStyle: { color: "#18181b" },
      subtextStyle: { color: "#52525b" },
    },
    gauge: {
      axisLine: {
        lineStyle: {
          color: [[1, "#e4e4e7"]],
        },
      },
      axisTick: { lineStyle: { color: "#d4d4d8" } },
      splitLine: { lineStyle: { color: "#d4d4d8" } },
      axisLabel: { color: "#52525b" },
      detail: {
        color: "#18181b",
      },
      title: {
        color: "#52525b",
      },
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: "#d4d4d8" } },
      axisTick: { lineStyle: { color: "#d4d4d8" } },
      axisLabel: { color: "#52525b" },
      splitLine: { lineStyle: { color: "#e4e4e7" } },
    },
    valueAxis: {
      axisLine: { lineStyle: { color: "#d4d4d8" } },
      axisTick: { lineStyle: { color: "#d4d4d8" } },
      axisLabel: { color: "#52525b" },
      splitLine: { lineStyle: { color: "#e4e4e7" } },
    },
    legend: {
      textStyle: { color: "#52525b" },
    },
    tooltip: {
      backgroundColor: "#ffffff",
      borderColor: "#e4e4e7",
      textStyle: { color: "#18181b" },
    },
  });
}

export function registerPulseDarkTheme(): void {
  registerPulseThemes();
}
