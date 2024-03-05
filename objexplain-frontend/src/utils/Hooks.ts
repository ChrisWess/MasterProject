import {getRequest} from "../api/requests";
import {login} from "../reducers/userSlice";
import {useDispatch, useSelector} from "react-redux";
import {useEffect} from "react";

export const useLoadUser = () => {
    const userInfo = useSelector((state: any) => state.user.value);
    const dispatch = useDispatch()

    const exec = async () => {
        let data = await getRequest('user/demo', undefined)
        if (data) {
            data = data.result
            dispatch(login(data))
            return data
        }
        return undefined
    };

    useEffect(() => {
        if (userInfo) {
            console.log('Logged in as: ' + userInfo.email)
        } else {
            exec().then(user => user ?
                console.log('Logging in as: ' + user.email) :
                console.log('Log in failed!'));
        }
    }, []);
}
