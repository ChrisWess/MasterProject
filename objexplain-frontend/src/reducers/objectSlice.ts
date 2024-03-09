import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {VisualFeature} from "../api/models/feature";
import {DetectedObject} from "../api/models/object";

interface ObjectPageState {
    objIdx: number | undefined;
    detObj: DetectedObject | undefined;
    showFeatures: boolean;
    featuresVis: boolean[] | undefined;
    features: VisualFeature | undefined;
}

const initialState: ObjectPageState = {
    objIdx: undefined,
    detObj: undefined,
    showFeatures: true,
    featuresVis: undefined,
    features: undefined,
};

export const objectPageSlice = createSlice({
    name: "object",
    initialState,
    reducers: {
        setObjectIdx: (state, action: PayloadAction<number>) => {
            state.objIdx = action.payload;
        },
        clearObjectIdx: (state) => {
            state.objIdx = undefined;
        },
        setObject: (state, action: PayloadAction<DetectedObject>) => {
            state.detObj = action.payload;
        },
        clearObject: (state) => {
            state.detObj = undefined;
        },
        switchFeaturesVisible: (state) => {
            state.showFeatures = !state.showFeatures;
        },
        switchFeatVisible: (state, action: PayloadAction<number>) => {
            let payload = action.payload;
            if (state.featuresVis && payload >= 0 && payload < state.featuresVis.length) {
                let prev = state.featuresVis;
                prev[payload] = !prev[payload];
                state.featuresVis = prev;
            }
        },
        setFeatures: (state, action: PayloadAction<VisualFeature>) => {
            state.features = action.payload;
        },
    }
});

// actions
export const {
    setObjectIdx, clearObjectIdx, switchFeaturesVisible,
    setObject, clearObject, switchFeatVisible, setFeatures,
} = objectPageSlice.actions;

export default objectPageSlice.reducer;