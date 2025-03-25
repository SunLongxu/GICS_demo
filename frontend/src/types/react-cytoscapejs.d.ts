declare module 'react-cytoscapejs' {
  import { Component } from 'react';
  import { Core, CytoscapeOptions, Stylesheet, LayoutOptions, ElementDefinition } from 'cytoscape';

  interface CytoscapeComponentProps {
    id?: string;
    cy?: (cy: Core) => void;
    style?: React.CSSProperties;
    elements: ElementDefinition[];
    layout?: LayoutOptions;
    stylesheet?: Stylesheet[];
    className?: string;
    zoom?: number;
    pan?: { x: number; y: number };
    minZoom?: number;
    maxZoom?: number;
    zoomingEnabled?: boolean;
    userZoomingEnabled?: boolean;
    panningEnabled?: boolean;
    userPanningEnabled?: boolean;
    boxSelectionEnabled?: boolean;
    autoungrabify?: boolean;
    autounselectify?: boolean;
  }

  class CytoscapeComponent extends Component<CytoscapeComponentProps> {}

  export default CytoscapeComponent;
} 