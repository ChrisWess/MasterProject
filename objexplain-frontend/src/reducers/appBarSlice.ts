import {createSlice, PayloadAction} from "@reduxjs/toolkit";

interface AppBarState {
    title: string;
}

const initialState: AppBarState = {
    title: 'ObjeXplain',
};

export const appBarSlice = createSlice({
    name: "appBar",
    initialState,
    reducers: {
        setTitle: (state, action: PayloadAction<string>) => {
            state.title = action.payload;
        },
        reset: () => initialState,
    },
});

export const {setTitle, reset} = appBarSlice.actions;

export default appBarSlice.reducer;
