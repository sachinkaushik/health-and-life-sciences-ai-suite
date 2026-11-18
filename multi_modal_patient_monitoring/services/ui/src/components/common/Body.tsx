// src/components/common/Body.tsx
import React, { useState } from "react";
import LeftPanel from "../LeftPanel/LeftPanel";
import RightPanel from "../RightPanel/RightPanel";
import CentralStation from "../CentralStation/CentralStation";
import { useAppSelector } from "../../redux/hooks";
import "../../assets/css/Body.css";

const Body: React.FC = () => {
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] = useState(false);
  const view = useAppSelector((state) => state.app.view);

  const toggleRightPanel = () => {
    setIsRightPanelCollapsed(!isRightPanelCollapsed);
  };

  if (view === 'central') {
    return (
      <div className="container">
        <CentralStation />
      </div>
    );
  }

  return (
    <div className="container">
      {/* Left Panel - always visible */}
      <div className="left-panel">
        <LeftPanel />
      </div>

      {/* Right Panel - toggles independently */}
      {!isRightPanelCollapsed && (
        <div className="right-panel">
          <RightPanel />
        </div>
      )}

      {/* Arrow - independent toggle */}
      <div
        className={`arrow${isRightPanelCollapsed ? ' collapsed' : ''}`}
        onClick={toggleRightPanel}
        title={isRightPanelCollapsed ? 'Show right panel' : 'Hide right panel'}
      >
        {isRightPanelCollapsed ? "◀" : "▶"}
      </div>
    </div>
  );
};

export default Body;