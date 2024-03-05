import axios from "axios";

const baseUrl: string = 'http://127.0.0.1:5000'
const loginEndpoint: string = '/login'

const httpClient = axios.create({
    withCredentials: true,
});

const handleError = (error: any, raise_errors: boolean) => {
    let fromAxios = axios.isAxiosError(error)
    if (fromAxios) {
        console.log('error message: ', error.message);
    } else {
        console.log('unexpected error: ', error);
    }
    if (raise_errors) {
        throw error
    } else if (fromAxios) {
        return error.message;
    } else {
        return 'An unexpected error occurred';
    }
}

export const getRequest = async (urlPath: string, identifier: string | undefined = undefined, params: any | undefined = undefined,
                                 raise_errors: boolean = false) => {
    if (identifier) {
        urlPath = `${baseUrl}/${urlPath}/${identifier}`
    } else {
        urlPath = `${baseUrl}/${urlPath}`
    }
    try {
        const {data} = await httpClient.get(
            urlPath,
            {
                headers: {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json',
                },
                params: params,
            },
        )
        if (data.status === 200) {
            return data
        } else if (data.status === 401) {
            window.location.href = baseUrl + loginEndpoint
        }
        // console.log(data)
        return undefined
    } catch (error) {
        handleError(error, raise_errors)
        return undefined
    }
}

export const loadImage = async (urlPath: string, entityId: string | undefined = undefined, raise_errors: boolean = false) => {
    // Load image from DB and create a temp image URL in order to be able to display the image.
    if (entityId) {
        urlPath = `${baseUrl}/${urlPath}/${entityId}`
    } else {
        urlPath = `${baseUrl}/${urlPath}`
    }
    try {
        const {data} = await axios.get(
            urlPath,
            {
                responseType: 'blob',
                headers: {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'image/jpeg',
                },
                withCredentials: false,
            },
        );
        if (data.type.startsWith('image')) {
            return URL.createObjectURL(data);
        }
        return undefined
    } catch (error) {
        handleError(error, raise_errors)
        return undefined
    }
}

export const postRequest = async (urlPath: string, postData: any, contentType: string | undefined = undefined,
                                  params: any | undefined = undefined, raise_errors: boolean = false) => {
    if (contentType === undefined) {
        contentType = 'application/json'
    }
    try {
        const {data} = await httpClient.post(
            `${baseUrl}/${urlPath}`,
            postData,
            {
                headers: {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': contentType,
                    Accept: 'application/json',
                },
                params: params,
            },
        )
        if (data.status === 201) {
            return data
        } else if (data.status === 401) {
            window.location.href = baseUrl + loginEndpoint
        }
        return undefined
    } catch (error) {
        handleError(error, raise_errors)
        return undefined
    }
}

export const putRequest = async (urlPath: string, putData: any, entityId: string | undefined = undefined,
                                 contentType: string | undefined = undefined, params: any | undefined = undefined,
                                 raise_errors: boolean = false) => {
    if (entityId) {
        urlPath = `${baseUrl}/${urlPath}/${entityId}`
    } else {
        urlPath = `${baseUrl}/${urlPath}`
    }
    if (contentType === undefined) {
        contentType = 'application/json'
    }
    try {
        const {data} = await httpClient.put(
            urlPath, putData,
            {
                headers: {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': contentType,
                    Accept: 'application/json',
                },
                params: params,
            },
        );
        if (data.status === 200) {
            return data
        } else if (data.status === 401) {
            window.location.href = baseUrl + loginEndpoint
        }
        return undefined
    } catch (error) {
        handleError(error, raise_errors)
        return undefined
    }
}

export const deleteRequest = async (urlPath: string, entityId: string | undefined = undefined,
                                    params: any | undefined = undefined, raise_errors: boolean = false) => {
    if (entityId) {
        urlPath = `${baseUrl}/${urlPath}/${entityId}`
    } else {
        urlPath = `${baseUrl}/${urlPath}`
    }
    try {
        const {data} = await httpClient.delete(
            urlPath,
            {
                headers: {
                    'Access-Control-Allow-Origin': '*',
                },
                params: params,
            },
        )
        if (data.status === 200) {
            return data
        } else if (data.status === 401) {
            window.location.href = baseUrl + loginEndpoint
        }
        return undefined
    } catch (error) {
        handleError(error, raise_errors)
        return undefined
    }
}
