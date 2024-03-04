import {useAxiosGet} from "../hooks/useAxios";

const ConfigPage = () => {
  const { data, error, loaded } = useAxiosGet('config');

  return (
    <div>
      <h1>Config</h1>
      <p>{loaded ? JSON.stringify(data) : "Loading..."}</p>
    </div>
  );
}

export default ConfigPage;
