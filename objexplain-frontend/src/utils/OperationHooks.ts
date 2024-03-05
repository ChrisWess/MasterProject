import axios from "axios";
import {useDispatch} from "react-redux";
import {addDoc, clearChanges} from "../reducers/operationsSlice";


// TODO: create hooks that save changes in the client and submit these only when the client is done:
//  https://react.dev/learn/reusing-logic-with-custom-hooks
export const useAddOp = (docId: string, opEntry: string[]) => {
    const dispatch = useDispatch()
    dispatch(addDoc(docId))

    if (localStorage.getItem("docId") === null) {
        localStorage.setItem("docId", docId)
    }
    localStorage.setItem("ops", JSON.stringify(opEntry))
}

function clearChange() {
    // Clear storage of unsaved changes
    const dispatch = useDispatch()
    dispatch(clearChanges())
    localStorage.removeItem("ops")
    localStorage.removeItem("docId")
}

async function saveChanges() {
    let ops: string | null = localStorage.getItem("ops")
    let docId: string | null = localStorage.getItem("docId")
    if (!!ops && !!docId) {
        try {
            const {data} = await axios.put(
                `http://127.0.0.1:5000/doc/${docId}`,
                {ops: ops},
                {
                    headers: {
                        'Access-Control-Allow-Origin': '*',
                    },
                },
            );

            if (data.status === 200) {
                clearChanges()
            }
        } catch (error) {
            if (axios.isAxiosError(error)) {
                console.log('error message: ', error.message);
                return error.message;
            } else {
                console.log('unexpected error: ', error);
                return 'An unexpected error occurred';
            }
        }
    }
}

const applyDocOperation = function (target: number[][][], op: number[]) {
    if (op[0] === 0) {
        let clusterIdx = op[1]
        let mentionIdx = op[2]
        let start = op[3]
        let end = op[4]
        // return insertCoref(target, clusterIdx, mentionIdx, start, end)
    } else if (op[0] === 1) {
        let clusterIdx = op[1]
        let mentionIdx = op[2]
        // return deleteCoref(target, clusterIdx, mentionIdx)
    } else {
        throw "Operation not permitted"
    }
}

function reapplyChanges(target: number[][][], ops: number[][]) {
    if (ops) {
        // re-apply doc changes in Frontend
        let targetCopy: number[][][] = target // _.cloneDeep(target)
        try {
            for (let op of ops) {
                targetCopy = [[[]]]  // applyDocOperation(targetCopy, op)
            }
            target = targetCopy
        } catch (error) {
            clearChanges()
        }
    }
    return target
}
