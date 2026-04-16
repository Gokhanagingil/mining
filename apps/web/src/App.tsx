import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { UploadPage } from './pages/UploadPage';
import { DatasetsPage } from './pages/DatasetsPage';
import { DatasetDetailPage } from './pages/DatasetDetailPage';
import { AnalysisResultsPage } from './pages/AnalysisResultsPage';
import { JobsPage } from './pages/JobsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<UploadPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="datasets/:id" element={<DatasetDetailPage />} />
          <Route path="datasets/:id/results" element={<AnalysisResultsPage />} />
          <Route path="jobs" element={<JobsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
