import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {BoundingBoxCoords} from "../api/models/feature";

interface FeaturesPageState {
    conceptIdx: number | undefined;
    currBbox: BoundingBoxCoords | undefined,
    bboxs: BoundingBoxCoords[];
    showPrevInput: boolean;
    isMoveObjImg: boolean;
    bboxsVis: boolean[];
}

const initialState: FeaturesPageState = {
    conceptIdx: undefined,
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
        setCurrBbox: (state, action: PayloadAction<BoundingBoxCoords>) => {
            state.currBbox = action.payload;
        },
        addBbox: (state) => {
            let curr = state.currBbox
            if (curr) {
                let bboxs = state.bboxs
                let visArr = state.bboxsVis
                bboxs.push(curr);
                visArr.push(true)
                state.bboxs = bboxs
                state.bboxsVis = visArr
                state.currBbox = undefined
            }
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
    setConceptIdx, setCurrBbox, addBbox,
    switchBboxVisible, clearFeaturePage, toggleObjMovable,
    toggleShowPrevBboxs,
} = featurePageSlice.actions;

export default featurePageSlice.reducer;