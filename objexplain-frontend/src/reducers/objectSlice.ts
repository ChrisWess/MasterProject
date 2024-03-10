import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {VisualFeature} from "../api/models/feature";
import {DetectedObject} from "../api/models/object";
import {Label} from "../api/models/label";

interface ObjectPageState {
    objIdx: number | undefined;
    detObj: DetectedObject | undefined;
    objectLabel: Label | undefined;
    showFeatures: boolean;
    featuresVis: boolean[] | undefined;
    features: VisualFeature | undefined;
}

const initialState: ObjectPageState = {
    objIdx: undefined,
    detObj: undefined,
    objectLabel: undefined,
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
        setObject: (state, action: PayloadAction<DetectedObject>) => {
            state.detObj = action.payload;
        },
        setObjectLabel: (state, action: PayloadAction<Label>) => {
            state.objectLabel = action.payload;
        },
        clearObject: (state) => {
            state.objIdx = undefined;
            state.objectLabel = undefined;
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
    setObjectIdx, switchFeaturesVisible, setObject,
    setObjectLabel, clearObject, switchFeatVisible,
    setFeatures,
} = objectPageSlice.actions;

export default objectPageSlice.reducer;