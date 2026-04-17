import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import EvaluatePage from "./pages/EvaluatePage";
import MonitoringPage from "./pages/MonitoringPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<EvaluatePage />} />
          <Route path="monitoring" element={<MonitoringPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
