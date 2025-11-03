import { Link, Outlet } from "react-router-dom";
import { Header, Footer } from "./components";
function App() {
  return (
    <>
      <Header />
      <main className="min-h-[70vh] bg-white text-gray-900 transition-colors">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}

export default App;
