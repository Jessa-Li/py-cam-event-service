import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';

import Login from './routes/Login';
import Dashboard from './routes/Dashboard';
import { getToken, isTokenValid } from './auth';

import './index.css';

function RequireAuth({ children }: { children: React.ReactNode }) {
  return isTokenValid(getToken()) ? <>{children}</> : <Navigate to="/login" replace />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Outlet />}>
          <Route index element={<Navigate to="/app" replace />} />
          <Route path="login" element={<Login />} />
          <Route
            path="app"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
