import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ToastProvider } from "./context/ToastContext.jsx";
import { StatusProvider } from "./context/StatusContext.jsx";
import Shell from "./components/layout/Shell.jsx";
import FeedPage from "./features/feed/FeedPage.jsx";
import TablePage from "./features/table/TablePage.jsx";
import KeywordsPage from "./features/keywords/KeywordsPage.jsx";
import SystemPage from "./features/system/SystemPage.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <StatusProvider>
          <Routes>
            <Route element={<Shell />}>
              <Route path="/" element={<FeedPage />} />
              <Route path="/table" element={<TablePage />} />
              <Route path="/keywords" element={<KeywordsPage />} />
              <Route path="/system" element={<SystemPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </StatusProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
