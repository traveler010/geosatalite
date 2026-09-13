import { createContext, useContext, useReducer, useCallback } from 'react';

// ─── Predefined Locations ───────────────────────────────

export const LOCATIONS = {
  'Sriharikota Spaceport': { latitude: 13.7199, longitude: 80.2304, altitude: 3000 },
  'Mumbai Port / JNPT': { latitude: 18.9500, longitude: 72.9500, altitude: 3000 },
  'Pangong Tso Basin': { latitude: 33.7595, longitude: 78.6674, altitude: 3000 },
  'Delhi IGI Airport Runway': { latitude: 28.5562, longitude: 77.1000, altitude: 3000 },
  'Visakhapatnam Port': { latitude: 17.6868, longitude: 83.2185, altitude: 3000 },
  'Suez Canal': { latitude: 30.5852, longitude: 32.2654, altitude: 3000 },
  'India': { latitude: 20.5937, longitude: 78.9629, altitude: 1800000 },
};

// ─── Initial State ──────────────────────────────────────

const initialState = {
  activeLocation: { ...LOCATIONS.India },
  locationLabel: '',
  cameraAltitude: '--',
  cameraCenter: '--',
  modality: 'Optical RGB',
  entityCount: 0,
  messages: [
    {
      id: 'init-1',
      type: 'assistant',
      text: '3D Earth console initialized. I can navigate global imagery, project an uploaded footprint, and annotate detected targets directly on the terrain.',
      result: 'THREE.JS / WORLD IMAGERY / READY',
    },
  ],
  uploadedFile: null,
  uploadedDataUrl: null,
  isQuerying: false,
  flyToTarget: null, // { latitude, longitude, altitude } — consumed by globe
  analysisEntities: [], // [{ lat, lng, label, color, type }]
};

// ─── Action Types ───────────────────────────────────────

const SET_LOCATION = 'SET_LOCATION';
const UPDATE_TELEMETRY = 'UPDATE_TELEMETRY';
const SET_MODALITY = 'SET_MODALITY';
const ADD_MESSAGE = 'ADD_MESSAGE';
const SET_QUERYING = 'SET_QUERYING';
const FLY_TO = 'FLY_TO';
const CLEAR_FLY_TARGET = 'CLEAR_FLY_TARGET';
const SET_UPLOAD = 'SET_UPLOAD';
const SET_ENTITIES = 'SET_ENTITIES';
const CLEAR_ENTITIES = 'CLEAR_ENTITIES';

// ─── Reducer ────────────────────────────────────────────

function appReducer(state, action) {
  switch (action.type) {
    case SET_LOCATION:
      return {
        ...state,
        activeLocation: action.payload.location,
        locationLabel: action.payload.label || '',
      };
    case UPDATE_TELEMETRY:
      return {
        ...state,
        cameraAltitude: action.payload.altitude,
        cameraCenter: action.payload.center,
      };
    case SET_MODALITY:
      return { ...state, modality: action.payload };
    case ADD_MESSAGE:
      return {
        ...state,
        messages: [...state.messages, {
          id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          ...action.payload,
        }],
      };
    case SET_QUERYING:
      return { ...state, isQuerying: action.payload };
    case FLY_TO:
      return {
        ...state,
        flyToTarget: action.payload.location,
        activeLocation: action.payload.location,
        locationLabel: action.payload.label || '',
      };
    case CLEAR_FLY_TARGET:
      return { ...state, flyToTarget: null };
    case SET_UPLOAD:
      return {
        ...state,
        uploadedFile: action.payload.file,
        uploadedDataUrl: action.payload.dataUrl,
      };
    case SET_ENTITIES:
      return {
        ...state,
        analysisEntities: action.payload,
        entityCount: action.payload.length,
      };
    case CLEAR_ENTITIES:
      return { ...state, analysisEntities: [], entityCount: 0 };
    default:
      return state;
  }
}

// ─── Context ────────────────────────────────────────────

const AppStoreContext = createContext(null);

export function AppStoreProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const actions = {
    setLocation: useCallback((location, label) => {
      dispatch({ type: SET_LOCATION, payload: { location, label } });
    }, []),

    updateTelemetry: useCallback((altitude, center) => {
      dispatch({ type: UPDATE_TELEMETRY, payload: { altitude, center } });
    }, []),

    setModality: useCallback((modality) => {
      dispatch({ type: SET_MODALITY, payload: modality });
    }, []),

    addMessage: useCallback((type, text, result = null) => {
      dispatch({ type: ADD_MESSAGE, payload: { type, text, result } });
    }, []),

    setQuerying: useCallback((isQuerying) => {
      dispatch({ type: SET_QUERYING, payload: isQuerying });
    }, []),

    flyTo: useCallback((location, label) => {
      dispatch({ type: FLY_TO, payload: { location, label } });
    }, []),

    clearFlyTarget: useCallback(() => {
      dispatch({ type: CLEAR_FLY_TARGET });
    }, []),

    setUpload: useCallback((file, dataUrl) => {
      dispatch({ type: SET_UPLOAD, payload: { file, dataUrl } });
    }, []),

    setEntities: useCallback((entities) => {
      dispatch({ type: SET_ENTITIES, payload: entities });
    }, []),

    clearEntities: useCallback(() => {
      dispatch({ type: CLEAR_ENTITIES });
    }, []),
  };

  return (
    <AppStoreContext.Provider value={{ state, actions }}>
      {children}
    </AppStoreContext.Provider>
  );
}

export function useAppStore() {
  const context = useContext(AppStoreContext);
  if (!context) {
    throw new Error('useAppStore must be used within AppStoreProvider');
  }
  return context;
}
