"use client";

import React, { useState, ChangeEvent } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Upload, CheckCircle, TrendingUp, AlertTriangle, Table } from "lucide-react";

interface RecordItem {
  Year: number;
  Month: number;
  Date: string;
  Label: string;
  Value: number;
  MoM_Growth: number;
}

interface SummaryData {
  total_months: number;
  min_cpi: number;
  max_cpi: number;
  avg_cpi: number;
  avg_monthly_growth: number;
  peak_spike: {
    label: string;
    growth_percentage: number;
  };
}

interface ApiResponse {
  items_available: string[];
  selected_item: string;
  summary: SummaryData;
  records: RecordItem[];
  error?: string;
}

export default function Home() {
  const [loading, setLoading] = useState<boolean>(false);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [fileName, setFileName] = useState<string>("");

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/analyze-fao-cpi", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Processing failed");
      }

      const result: ApiResponse = await res.json();
      setData(result);
    } catch (error: unknown) {
      console.error("Error communicating with Python API:", error);
      const msg = error instanceof Error ? error.message : "Failed to analyze dataset";
      alert(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-800 p-6 md:p-12">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* HEADER */}
        <header className="text-center space-y-2">
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight flex items-center justify-center gap-3">
            <TrendingUp className="w-9 h-9 text-blue-600" />
            FAOSTAT CPI Data Analyzer
          </h1>
          <p className="text-slate-600 max-w-xl mx-auto">
            Upload your FAOSTAT CSV file to clean month codes and analyze 
            inflation trends powered by Python Pandas and Next.js.
          </p>
        </header>

        {/* FILE UPLOAD BOX */}
        <div className="bg-white border-2 border-dashed border-slate-300 rounded-2xl p-8 text-center hover:border-blue-500 transition shadow-sm">
          <input
            type="file"
            accept=".csv"
            onChange={handleFileUpload}
            id="cpiInput"
            className="hidden"
          />
          <label htmlFor="cpiInput" className="cursor-pointer space-y-3 block">
            <div className="w-14 h-14 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto">
              <Upload className="w-7 h-7" />
            </div>
            <div>
              <span className="font-semibold text-blue-600 hover:underline">
                Click to upload FAOSTAT CSV
              </span>
            </div>
            {fileName && (
              <p className="text-xs text-emerald-600 font-medium flex items-center justify-center gap-1">
                <CheckCircle className="w-4 h-4" /> Selected File: {fileName}
              </p>
            )}
          </label>
        </div>

        {loading && (
          <div className="text-center py-8 font-semibold text-blue-600 animate-pulse">
            🐍 Python serverless function cleaning & analyzing dataset...
          </div>
        )}

        {/* DASHBOARD DISPLAY */}
        {data && !loading && (
          <div className="space-y-8">
            
            {/* KPI STAT CARDS */}
            <section className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-xs font-semibold text-slate-400 uppercase">Total Months</p>
                <p className="text-2xl font-bold text-slate-800">{data.summary.total_months}</p>
              </div>
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-xs font-semibold text-slate-400 uppercase">Lowest CPI</p>
                <p className="text-2xl font-bold text-emerald-600">{data.summary.min_cpi}</p>
              </div>
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-xs font-semibold text-slate-400 uppercase">Highest CPI</p>
                <p className="text-2xl font-bold text-rose-600">{data.summary.max_cpi}</p>
              </div>
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-xs font-semibold text-slate-400 uppercase">Average CPI</p>
                <p className="text-2xl font-bold text-blue-600">{data.summary.avg_cpi}</p>
              </div>
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm col-span-2 md:col-span-1">
                <p className="text-xs font-semibold text-slate-400 uppercase">Avg MoM Growth</p>
                <p className="text-2xl font-bold text-purple-600">{data.summary.avg_monthly_growth}%</p>
              </div>
            </section>

            {/* PEAK INFLATION BANNER */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3 text-amber-900 text-sm">
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
              <span>
                <strong>Highest Inflation Spike:</strong> An increase of{" "}
                <strong>+{data.summary.peak_spike.growth_percentage}%</strong> occurred in{" "}
                <strong>{data.summary.peak_spike.label}</strong>.
              </span>
            </div>

            {/* CPI LINE CHART */}
            <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-800 text-lg">
                📈 Historical CPI Index Trend ({data.selected_item})
              </h3>
              <div className="h-80 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.records}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="Label" stroke="#64748b" fontSize={11} minTickGap={30} />
                    <YAxis stroke="#64748b" fontSize={12} domain={["auto", "auto"]} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const record = payload[0].payload as RecordItem;
                          return (
                            <div className="bg-slate-900 text-white p-3 rounded-lg text-xs space-y-1 shadow-lg">
                              <p className="font-bold border-b border-slate-700 pb-1">{record.Label}</p>
                              <p>CPI Index: <span className="font-semibold text-blue-400">{record.Value}</span></p>
                              <p>MoM Growth: <span className="font-semibold text-emerald-400">{record.MoM_Growth > 0 ? `+${record.MoM_Growth}` : record.MoM_Growth}%</span></p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="Value"
                      stroke="#2563eb"
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* DATA TABLE */}
            <section className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              <h3 className="font-bold text-slate-800 text-lg flex items-center gap-2">
                <Table className="w-5 h-5 text-blue-600" /> Python Pandas Output Preview
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600 border-collapse">
                  <thead>
                    <tr className="bg-slate-100 border-b border-slate-200 text-slate-700 font-bold">
                      <th className="p-3">Formatted Date</th>
                      <th className="p-3">Year</th>
                      <th className="p-3">Month</th>
                      <th className="p-3">CPI Value</th>
                      <th className="p-3">MoM Growth (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.records.slice(-10).map((row, idx) => (
                      <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3 font-semibold">{row.Label}</td>
                        <td className="p-3">{row.Year}</td>
                        <td className="p-3">{row.Month}</td>
                        <td className="p-3 font-medium text-slate-900">{row.Value}</td>
                        <td className={`p-3 font-semibold ${row.MoM_Growth >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                          {row.MoM_Growth >= 0 ? `+${row.MoM_Growth}` : row.MoM_Growth}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

          </div>
        )}

      </div>
    </main>
  );
}