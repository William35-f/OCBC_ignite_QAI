import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { Placeholder } from "./components/ui";
import KnowledgeBase from "./pages/KnowledgeBase";
import Settings from "./pages/Settings";
import { USERS, useRole } from "./roles";

function Home() {
  const { role } = useRole();
  return <Navigate to={USERS[role].home} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="chat" element={<Placeholder title="Ask OCBC AI" phase={2} />} />
        <Route path="review" element={<Placeholder title="Review queue" phase={5} />} />
        <Route path="admin" element={<Placeholder title="Dashboard" phase={6} />} />
        <Route path="kb" element={<KnowledgeBase />} />
        <Route path="trust" element={<Placeholder title="Trust Challenge" phase={7} />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  );
}
