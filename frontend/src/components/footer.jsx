import React from "react";

export default function Footer() {
  return (
    <footer className="py-6 bg-gray-100 text-center text-sm text-gray-700 mt-8 transition-colors">
      <div className="max-w-7xl mx-auto px-4">
        © {new Date().getFullYear()} CareSentry. All rights reserved.
      </div>
    </footer>
  );
}
