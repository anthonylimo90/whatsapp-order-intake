import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { DemoPage } from './pages/DemoPage';
import { DashboardPage } from './pages/DashboardPage';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DemoPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
