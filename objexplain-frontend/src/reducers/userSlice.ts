import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {User} from "../api/models/user";


interface UserState {
    value: User | undefined;
}

const initialState: UserState = {
    value: undefined,
};


export const userSlice = createSlice({
    name: "user",
    initialState,
    reducers: {
        login: (state, action: PayloadAction<User>) => {
            state.value = action.payload;
        },
        logout: (state) => {
            state.value = undefined;
        },
    },
});

export const {login, logout} = userSlice.actions;

export default userSlice.reducer;
