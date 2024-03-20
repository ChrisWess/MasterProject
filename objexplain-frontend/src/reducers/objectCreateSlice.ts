import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {BoundingBoxCoords} from "../api/models/feature";

interface NewObjectPageState {
    showCurrObjs: boolean;
    isMoveImg: boolean;
    newBbox: BoundingBoxCoords | undefined;
}

const initialState: NewObjectPageState = {
    showCurrObjs: true,
    isMoveImg: false,
    newBbox: undefined,
};

export const newObjectPageSlice = createSlice({
    name: "newObj",
    initialState,
    reducers: {
        toggleShowObjs: (state) => {
            state.showCurrObjs = !state.showCurrObjs;
        },
        toggleMovable: (state) => {
            state.isMoveImg = !state.isMoveImg;
        },
        setBbox: (state, action: PayloadAction<BoundingBoxCoords>) => {
            state.newBbox = action.payload;
        },
        clearBbox: (state) => {
            state.newBbox = undefined;
        },
        clearUpdObjectView: (state) => {
            state.showCurrObjs = true;
            state.isMoveImg = false;
            state.newBbox = undefined;
        },
    }
});

export const {
    toggleShowObjs, toggleMovable, setBbox, clearBbox,
    clearUpdObjectView,
} = newObjectPageSlice.actions;

export default newObjectPageSlice.reducer;