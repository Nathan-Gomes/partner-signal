import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ToastProvider } from "./components/ui";
import { Capture } from "./pages/Capture";
import { Opportunity } from "./pages/Opportunity";
import { PartnerDetail, Partners } from "./pages/Partners";
import { Pipeline } from "./pages/Pipeline";
import { Playbook } from "./pages/Playbook";
import { Reports } from "./pages/Reports";
import { Signals } from "./pages/Signals";
import { Today } from "./pages/Today";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 15_000, retry: 2, refetchOnWindowFocus: false } },
});

function NotFound() {
  return (
    <div className="page">
      <h1>This page doesn't exist</h1>
      <p className="lede">
        <Link to="/">Go to today's queue</Link>
      </p>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Today />} />
              <Route path="signals" element={<Signals />} />
              <Route path="pipeline" element={<Pipeline />} />
              <Route path="partners" element={<Partners />} />
              <Route path="partners/:id" element={<PartnerDetail />} />
              <Route path="opportunities/:id" element={<Opportunity />} />
              <Route path="capture" element={<Capture />} />
              <Route path="reports" element={<Reports />} />
              <Route path="playbook" element={<Playbook />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
