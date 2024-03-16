import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {VisualFeature} from "../api/models/feature";
import {Annotation} from "../api/models/annotation";

interface AnnotationPageState {
    annotationIdx: number | undefined;
    annotation: Annotation | undefined;
    selectedConcept: number | undefined;
    markedWords: number[];
    wordFlags: boolean[] | undefined;
    markedWordsPrevColors: string[] | undefined;
    conceptSubstrings: string[] | undefined;
    conceptRanges: [number, number][] | undefined;
    objImgUrl: string | undefined;
    showFeatures: boolean;
    featuresVis: boolean[] | undefined;
    features: VisualFeature[] | undefined;
    showConcepts: boolean;
}

const initialState: AnnotationPageState = {
    annotationIdx: undefined,
    annotation: undefined,
    selectedConcept: undefined,
    markedWords: [],
    wordFlags: undefined,
    markedWordsPrevColors: undefined,
    conceptSubstrings: undefined,
    conceptRanges: undefined,
    objImgUrl: undefined,
    showFeatures: true,
    featuresVis: undefined,
    features: undefined,
    showConcepts: true,
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
        setSelectedConcept: (state, action: PayloadAction<number>) => {
            state.selectedConcept = action.payload;
        },
        clearSelectedConcept: (state) => {
            state.selectedConcept = undefined;
        },
        setWordFlags: (state, action: PayloadAction<boolean[]>) => {
            state.wordFlags = action.payload;
        },
        setMarkedWords: (state, action: PayloadAction<number[]>) => {
            state.markedWords = action.payload;
        },
        setPrevColors: (state, action: PayloadAction<string[]>) => {
            state.markedWordsPrevColors = action.payload;
        },
        setConceptSubs: (state, action: PayloadAction<string[]>) => {
            state.conceptSubstrings = action.payload;
        },
        setConceptRanges: (state, action: PayloadAction<[number, number][]>) => {
            state.conceptRanges = action.payload;
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
        initVisibleFeatures: (state, action: PayloadAction<number>) => {
            state.featuresVis = Array(action.payload).fill(true);
        },
        addVisibleFeature: (state) => {
            if (state.featuresVis) {
                state.featuresVis = [...state.featuresVis, true];
            }
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
    setAnnotationIdx, setAnnotation, setSelectedConcept, clearSelectedConcept,
    setWordFlags, setMarkedWords, setPrevColors, setConceptSubs,
    setConceptRanges, setObjImgUrl, initVisibleFeatures, addVisibleFeature,
    switchFeaturesVisible, switchFeatVisible, setFeatures,
} = annotationPageSlice.actions;

export default annotationPageSlice.reducer;