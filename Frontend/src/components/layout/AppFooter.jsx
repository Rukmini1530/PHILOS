import React from "react";

const AppFooter = () => {
  return React.createElement(
    "footer",
    {
      className: "bg-gray-900 border-t border-gray-800 py-3 px-6 text-sm text-gray-500"
    },
    React.createElement(
      "div",
      { className: "max-w-7xl mx-auto" },
      React.createElement(
        "div",
        { className: "flex items-center justify-between" },
        React.createElement(
          "div",
          null,
          React.createElement("span", null, "PHILOS")
        ),
        React.createElement(
          "span",
          null,
          "Explore beyond the visible."
        )
      )
    )
  );
};

export default AppFooter;