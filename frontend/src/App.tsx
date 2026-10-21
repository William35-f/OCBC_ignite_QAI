import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { Placeholder } from "./components/ui";
import Chat from "./pages/Chat";
import KnowledgeBase from "./pages/KnowledgeBase";
import ReviewDetail from "./pages/ReviewDetail";
import ReviewQueue from "./pages/ReviewQueue";
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
        <Route path="chat" element={<Chat />} />
        <Route path="review" element={<ReviewQueue />} />
        <Route path="review/:id" element={<ReviewDetail />} />
        <Route path="admin" element={<Placeholder title="Dashboard" phase={6} />} />
        <Route path="kb" element={<KnowledgeBase />} />
        <Route path="trust" element={<Placeholder title="Trust Challenge" phase={7} />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  );
}
