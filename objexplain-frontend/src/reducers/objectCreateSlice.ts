import {createSlice, PayloadAction} from "@reduxjs/toolkit";

type Bbox = { tlx: number; tly: number; brx: number; bry: number };

interface NewObjectPageState {
    isMoveImg: boolean;
    newBbox: Bbox | undefined;
}

const initialState: NewObjectPageState = {
    isMoveImg: true,
    newBbox: undefined,
};

export const newObjectPageSlice = createSlice({
    name: "newObj",
    initialState,
    reducers: {
        toggleMovable: (state) => {
            state.isMoveImg = !state.isMoveImg;
        },
        setBbox: (state, action: PayloadAction<Bbox>) => {
            state.newBbox = action.payload;
        },
        clearBbox: (state) => {
            state.newBbox = undefined;
        },
    }
});

export const {
    toggleMovable, setBbox, clearBbox
} = newObjectPageSlice.actions;

export default newObjectPageSlice.reducer;