import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {BoundingBoxCoords, VisualFeature} from "../api/models/feature";

interface FeaturesPageState {
    conceptIdx: number | undefined;
    visualFeature: VisualFeature | undefined;
    currBbox: BoundingBoxCoords | undefined,
    bboxs: BoundingBoxCoords[];
    showPrevInput: boolean;
    isMoveObjImg: boolean;
    bboxsVis: boolean[];
}

const initialState: FeaturesPageState = {
    conceptIdx: undefined,
    visualFeature: undefined,
    currBbox: undefined,
    bboxs: [],
    bboxsVis: [],
    showPrevInput: true,
    isMoveObjImg: false,
};

export const featurePageSlice = createSlice({
    name: "feature",
    initialState,
    reducers: {
        setConceptIdx: (state, action: PayloadAction<number>) => {
            state.conceptIdx = action.payload;
        },
        setFeature: (state, action: PayloadAction<VisualFeature>) => {
            state.visualFeature = action.payload;
        },
        setCurrBbox: (state, action: PayloadAction<BoundingBoxCoords>) => {
            state.currBbox = action.payload;
        },
        clearFeatureBbox: (state) => {
            state.currBbox = undefined;
        },
        addBbox: (state) => {
            let curr = state.currBbox
            if (curr) {
                let visArr = state.bboxsVis
                visArr.push(true)
                state.bboxs = [...state.bboxs, curr]
                state.bboxsVis = visArr
                state.currBbox = undefined
            }
        },
        initBboxVisibilities: (state) => {
            let feat = state.visualFeature
            let prevLength = feat?.bboxs ? feat.bboxs.length : 0
            state.bboxsVis = Array(prevLength).fill(true)
        },
        clearPrevBboxs: (state) => {
            state.bboxs = [];
        },
        switchBboxVisible: (state, action: PayloadAction<number>) => {
            let payload = action.payload;
            let visArr = state.bboxsVis
            if (visArr && payload >= 0 && payload < visArr.length) {
                visArr[payload] = !visArr[payload];
                state.bboxsVis = visArr;
            }
        },
        clearFeaturePage: (state) => {
            state.conceptIdx = undefined;
            state.visualFeature = undefined;
            state.currBbox = undefined
            state.bboxs = [];
            state.bboxsVis = [];
            state.showPrevInput = true;
            state.isMoveObjImg = false;
        },
        toggleShowPrevBboxs: (state) => {
            state.showPrevInput = !state.showPrevInput;
        },
        toggleObjMovable: (state) => {
            state.isMoveObjImg = !state.isMoveObjImg;
        },
    }
});

export const {
    setConceptIdx, setFeature, setCurrBbox, addBbox,
    clearFeatureBbox, initBboxVisibilities, clearPrevBboxs, switchBboxVisible,
    clearFeaturePage, toggleObjMovable, toggleShowPrevBboxs,
} = featurePageSlice.actions;

export default featurePageSlice.reducer;