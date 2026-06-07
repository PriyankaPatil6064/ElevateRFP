// components/Navbar.jsx
// 5 flat links: Home · Analyze RFP · Dashboard · Platform Catalog · About
// No dropdowns for links. User dropdown kept for sign in/out.

import { useState, useRef, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  Triangle, ChevronDown, LogOut, User
} from "lucide-react";

const NAV_LINKS = [
  { to: "/",         label: "Home" },
  { to: "/analyze",  label: "Analyze RFP",      auth: true },
  { to: "/dashboard",label: "Dashboard",         auth: true },
  { to: "/catalog",  label: "Platform Catalog" },
  { to: "/about",    label: "About" },
];

export default function Navbar() {
  const { pathname }                  = useLocation();
  const { isAuthenticated, logout, user } = useAuth();
  const [dropOpen, setDropOpen]       = useState(false);
  const dropRef                       = useRef(null);

  useEffect(() => {
    function handler(e) {
      if (dropRef.current && !dropRef.current.contains(e.target)) {
        setDropOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const initials = user?.name
    ? user.name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2)
    : "A";

  const visibleLinks = NAV_LINKS.filter(
    link => !link.auth || isAuthenticated
  );

  return (
    <nav className="rfp-navbar">
      <div className="navbar-inner">
        {/* Brand */}
        <Link to="/" className="brand-logo">
          <div className="brand-icon-wrap">
            <Triangle size={14} fill="currentColor" />
          </div>
          <span className="brand-name">
            Elevate<span className="brand-accent">RFP</span>
          </span>
        </Link>

        {/* Nav links */}
        <div className="nav-links">
          {visibleLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={`nav-link ${pathname === to ? "active" : ""}`}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* User area */}
        <div className="nav-user" ref={dropRef}>
          {isAuthenticated ? (
            <>
              <button
                className="nav-user-btn"
                onClick={() => setDropOpen(v => !v)}
              >
                <div className="nav-avatar">{initials}</div>
                <span>{user?.name || "Admin"}</span>
                <ChevronDown size={13} />
              </button>
              {dropOpen && (
                <div className="nav-dropdown">
                  <button
                    className="nav-dropdown-item danger"
                    onClick={() => { logout(); setDropOpen(false); }}
                  >
                    <LogOut size={13} />
                    Sign out
                  </button>
                </div>
              )}
            </>
          ) : (
            <Link to="/login" className="btn btn-outline btn-sm">
              <User size={13} />
              Sign in
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
