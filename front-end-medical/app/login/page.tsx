"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (email && password) {
      setIsLoading(true);

      try {
        const data = await login(email, password);

        if (data.user.must_change_password) {
          router.push("/change-password");
        } else if (data.user.role === "Doctors") {
          router.push("/dashboard");
        } else if (data.user.role === "Superadmin") {
          router.push("/admin");
        } else {
          // Default fallback
          router.push("/dashboard");
        }
      } catch (err: any) {
        setError(err.message || "Lỗi đăng nhập. Vui lòng kiểm tra lại thông tin.");
      } finally {
        setIsLoading(false);
      }
    } else {
      setError("Vui lòng nhập đầy đủ email và mật khẩu.");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50/80 p-4">
      <div className="w-full max-w-md rounded-xl border border-gray-100 bg-white p-8 shadow-sm">

        {/* Logo Icon */}
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm mb-6 mx-auto">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
        </div>

        {/* Heading */}
        <div className="mb-8 flex flex-col space-y-2 text-center">
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Medical Imaging</h1>
          <p className="text-sm text-gray-500 font-medium">
            Annotation & Analysis Platform
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-md bg-red-50 p-3 text-sm text-red-600 border border-red-100 text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5 focus-within:text-blue-600 text-gray-700">
            <label
              htmlFor="email"
              className="text-sm font-semibold select-none bg-white relative transition-colors"
            >
              Email Address
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex h-11 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-sm"
              required
            />
          </div>

          <div className="space-y-1.5 focus-within:text-blue-600 text-gray-700 pb-2">
            <label
              htmlFor="password"
              className="text-sm font-semibold select-none bg-white relative transition-colors"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="........"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="flex h-11 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-sm tracking-widest font-mono"
              required
              minLength={6}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="inline-flex h-11 w-full items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm disabled:pointer-events-none disabled:opacity-70"
          >
            {isLoading ? "Logging in..." : "Login"}
          </button>
        </form>

        <div className="mt-6 text-center text-xs text-gray-400">
          Hệ thống phân tích hình ảnh y khoa - 2026
        </div>
      </div>
    </div>
  );
}
