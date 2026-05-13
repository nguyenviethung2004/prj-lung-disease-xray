"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getAuthUser, logout } from "@/lib/api/auth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const authUser = getAuthUser();
    if (!authUser) {
      router.push("/login");
      return;
    }
    if (authUser.role !== "Superadmin") {
      if (authUser.role === "Doctors") {
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
      return;
    }

    if (authUser.must_change_password) {
      router.push("/change-password");
      return;
    }

    setUser(authUser);
  }, [router]);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  const navItems = [
    { name: "Overview", href: "/admin" },
    // { name: "New Training", href: "/admin/new-training" },
    // { name: "Training History", href: "/admin/training-history" },
    // { name: "Dataset", href: "/admin/dataset" },
    // { name: "Models", href: "/admin/models" },
    { name: "Users", href: "/admin/users" },
    { name: "Documents", href: "/admin/documents" },
    { name: "AI Reviews", href: "/admin/reviews" },
  ];

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 hidden md:flex flex-col sticky top-0 h-screen overflow-y-auto">
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <div className="flex items-center gap-2 font-semibold text-lg">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-600 text-white shadow-sm">
              <span className="text-sm font-bold">A</span>
            </div>
            Admin Panel
          </div>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  }`}
              >
                {item.name}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="sticky top-0 z-10 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center md:hidden">
            <span className="font-semibold text-lg">Admin Panel</span>
          </div>
          <div className="hidden md:block"></div> {/* Spacer */}

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-sm font-bold text-blue-700 border-2 border-white shadow-sm">
                {user ? user.username?.substring(0, 2).toUpperCase() || user.UserName?.substring(0, 2).toUpperCase() || "AD" : "..."}
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-gray-900 hidden sm:block leading-none">
                  {user ? user.username || user.UserName || "Admin User" : "Loading..."}
                </span>
                <span className="text-[10px] text-gray-500 font-medium hidden sm:block mt-1 uppercase tracking-tight">
                  {user?.role || "Administrator"}
                </span>
              </div>
            </div>
            <div className="h-6 w-px bg-gray-200"></div>
            <button
              onClick={handleLogout}
              className="inline-flex h-9 items-center justify-center rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-red-700 focus:outline-none shadow-sm"
            >
              Logout
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
