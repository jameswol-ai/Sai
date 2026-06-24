import streamlit as st
import importlib

def render_plugins_tab():
    st.title("Plugin Manager")

    # Registry of available plugins
    available_plugins = {
        "Risk Manager": "risk_plugin",
        "Notifier (Slack)": "slack_notifier",
        "Notifier (Email)": "email_notifier"
    }

    # Session state for toggles
    if "active_plugins" not in st.session_state:
        st.session_state.active_plugins = {}

    for name, module_name in available_plugins.items():
        enabled = st.checkbox(f"Enable {name}", 
                              value=st.session_state.active_plugins.get(module_name, False))
        
        if enabled:
            try:
                module = importlib.import_module(f"sai.plugins.{module_name}")
                if hasattr(module, "init_plugin"):
                    module.init_plugin()
                st.success(f"{name} loaded successfully.")
                st.session_state.active_plugins[module_name] = True
            except Exception as e:
                st.error(f"Failed to load {name}: {e}")
                st.session_state.active_plugins[module_name] = False
        else:
            st.session_state.active_plugins[module_name] = False

    # Health reporting
    st.subheader("Plugin Health")
    for module_name, active in st.session_state.active_plugins.items():
        status = "Active" if active else "Disabled"
        st.write(f"{module_name}: {status}")
