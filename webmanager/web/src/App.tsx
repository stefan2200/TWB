import React from 'react';
import {Outlet,} from "react-router-dom";
import ResponsiveAppBar from "./components/menu";


function App() {
  return (
    <>
      <ResponsiveAppBar/>
      <Outlet/>
    </>
  );
}

export default App;
