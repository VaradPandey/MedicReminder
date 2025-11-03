import { Link, Outlet } from "react-router-dom";
import { Header, Footer } from "./components";
function App() {
  return (
    <>
      <Header />
      <main className="min-h-[70vh] bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-gray-100 transition-colors">
        <Outlet />
      </main>
      <Footer />
    </>
  );
}

export default App;
