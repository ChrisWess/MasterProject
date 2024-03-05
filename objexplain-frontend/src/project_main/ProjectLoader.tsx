import {getRequest} from "../api/requests";


export const loadProject = async (path: any) => {
    const {projectName} = path.params
    const projectData = await getRequest('project/fromUser', encodeURIComponent(projectName))
    if (projectData) {
        return projectData.result
    }
    return null
}