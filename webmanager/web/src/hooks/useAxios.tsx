import {useEffect, useState} from "react";
import axios from "axios";

const BASE_URL = "http://127.0.0.1:5000/api"; // TODO: env or config

const useAxiosGet = (path: string) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    axios
      .get(`${BASE_URL}/${path}`)
      .then((response) => setData(response.data))
      .catch((error) => setError(error.message))
      .finally(() => setLoaded(true));
  }, []);

  return { data, error, loaded };
}

const useAxiosPost = (path: string, payload: object) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    axios
      .post(`${BASE_URL}/${path}`, payload)
      .then((response) => setData(response.data))
      .catch((error) => setError(error.message))
      .finally(() => setLoaded(true));
  }, []);

  return { data, error, loaded };
}

export { useAxiosGet };
