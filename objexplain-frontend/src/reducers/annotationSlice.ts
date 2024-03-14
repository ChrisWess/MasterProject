import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {VisualFeature} from "../api/models/feature";
import {Annotation} from "../api/models/annotation";

interface AnnotationPageState {
    annotationIdx: number | undefined;
    annotation: Annotation | undefined;
    conceptSubstrings: string[] | undefined;
    objImgUrl: string | undefined;
    showFeatures: boolean;
    featuresVis: boolean[] | undefined;
    features: VisualFeature[] | undefined;
}

const initialState: AnnotationPageState = {
    annotationIdx: undefined,
    annotation: undefined,
    conceptSubstrings: undefined,
    objImgUrl: undefined,
    showFeatures: true,
    featuresVis: undefined,
    features: undefined,
};

export const annotationPageSlice = createSlice({
    name: "annotation",
    initialState,
    reducers: {
        setAnnotationIdx: (state, action: PayloadAction<number>) => {
            state.annotationIdx = action.payload;
        },
        setAnnotation: (state, action: PayloadAction<Annotation>) => {
            state.annotation = action.payload;
        },
        setConceptSubs: (state, action: PayloadAction<string[]>) => {
            state.conceptSubstrings = action.payload;
        },
        setObjImgUrl: (state, action: PayloadAction<string>) => {
            state.objImgUrl = action.payload;
        },
        clearAnnotationView: (state) => {
            state.featuresVis = undefined;
            state.features = undefined;
            state.annotation = undefined;
            state.conceptSubstrings = undefined;
            state.objImgUrl = undefined;
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
        setFeatures: (state, action: PayloadAction<VisualFeature[]>) => {
            state.features = action.payload;
        },
    }
});

// actions
export const {
    setAnnotationIdx, setAnnotation, setConceptSubs,
    setObjImgUrl, switchFeaturesVisible, switchFeatVisible,
    setFeatures,
} = annotationPageSlice.actions;

export default annotationPageSlice.reducer;