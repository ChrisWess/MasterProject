import {getRequest} from "../api/requests";


export const loadIDoc = async (path: any) => {
    const {docId} = path.params
    const imageDoc = await getRequest('idoc', docId)
    if (imageDoc) {
        return imageDoc.result
    }
    return null
}