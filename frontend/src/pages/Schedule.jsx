import React from "react";
import { useLocation } from "react-router-dom";
import Scheduler from "../components/ScheduleSetup.jsx";
import PageWrapper from "../components/PageWrapper";

export default function SchedulePage() {
  const location = useLocation();
  const prefill = location.state?.prefill || null;

  return (
    <PageWrapper>
      <Scheduler extracted={prefill} />
    </PageWrapper>
  );
}
