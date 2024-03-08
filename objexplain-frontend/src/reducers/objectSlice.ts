import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {VisualFeature} from "../api/models/feature";

interface ObjectPageState {
    objIdx: number | undefined;
    showFeatures: boolean;
    featuresVis: boolean[] | undefined;
    features: VisualFeature | undefined;
}

const initialState: ObjectPageState = {
    objIdx: undefined,
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
    switchFeatVisible, setFeatures,
} = objectPageSlice.actions;

export default objectPageSlice.reducer;