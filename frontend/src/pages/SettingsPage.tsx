import { useState, useEffect } from 'react';
import { Settings, Check, X, Eye, EyeOff, Save, RefreshCw } from 'lucide-react';
import axios from 'axios';
import type { UserSettings, APIKeys, ValidationResult } from '../types/settings';

export const SettingsPage = () => {
  const [settings, setSettings] = useState<UserSettings>({
    api_keys: {},
    preferences: {
      default_data_source: 'opentopography',
      default_image_source: 'sentinel_hub',
      language: 'en'
    }
  });
  
  const [showSecrets, setShowSecrets] = useState<{ [key: string]: boolean }>({});
  const [validationStatus, setValidationStatus] = useState<{ [key: string]: ValidationResult | null }>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await axios.get<UserSettings>('/api/settings/');
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const handleAPIKeyChange = (key: keyof APIKeys, value: string) => {
    setSettings(prev => ({
      ...prev,
      api_keys: {
        ...prev.api_keys,
        [key]: value
      }
    }));
    // Clear validation status when key changes
    setValidationStatus(prev => ({ ...prev, [key]: null }));
  };

  const handlePreferenceChange = (key: string, value: string) => {
    setSettings(prev => ({
      ...prev,
      preferences: {
        ...prev.preferences,
        [key]: value
      }
    }));
  };

  const validateKey = async (service: string, key: string) => {
    if (!key) return;
    
    setValidationStatus(prev => ({ ...prev, [service]: { valid: false, message: 'Validating...' } }));
    
    try {
      const response = await axios.post<ValidationResult>(`/api/settings/validate/${service}`, null, {
        params: { api_key: key }
      });
      setValidationStatus(prev => ({ ...prev, [service]: response.data }));
    } catch (error) {
      setValidationStatus(prev => ({
        ...prev,
        [service]: { valid: false, error: 'Validation failed' }
      }));
    }
  };

  const saveSettings = async () => {
    setIsSaving(true);
    setSaveMessage(null);
    
    try {
      await axios.put('/api/settings/', settings);
      setSaveMessage({ type: 'success', text: 'Settings saved successfully!' });
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error) {
      setSaveMessage({ type: 'error', text: 'Failed to save settings' });
      setTimeout(() => setSaveMessage(null), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  const toggleShowSecret = (key: string) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const renderAPIKeyField = (
    label: string,
    key: keyof APIKeys,
    service: string,
    description: string,
    isSecret: boolean = false
  ) => {
    const value = settings.api_keys[key] || '';
    const status = validationStatus[service];
    
    return (
      <div className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              {label}
            </label>
            <p className="text-xs text-gray-500 mb-3">{description}</p>
          </div>
          {status && (
            <div className="ml-2">
              {status.valid ? (
                <Check className="text-green-500" size={20} />
              ) : (
                <X className="text-red-500" size={20} />
              )}
            </div>
          )}
        </div>
        
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type={isSecret && !showSecrets[key] ? 'password' : 'text'}
              value={value}
              onChange={(e) => handleAPIKeyChange(key, e.target.value)}
              placeholder={`Enter ${label}`}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {isSecret && (
              <button
                onClick={() => toggleShowSecret(key)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                type="button"
              >
                {showSecrets[key] ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            )}
          </div>
          
          <button
            onClick={() => validateKey(service, value)}
            disabled={!value}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            type="button"
          >
            <RefreshCw size={16} />
            Verify
          </button>
        </div>
        
        {status && status.message && (
          <p className="mt-2 text-sm text-gray-600">{status.message}</p>
        )}
        {status && status.error && (
          <p className="mt-2 text-sm text-red-600">{status.error}</p>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Settings size={32} className="text-blue-500" />
            <h1 className="text-3xl font-bold text-gray-800">Settings</h1>
          </div>
          <p className="text-gray-600">
            Manage your API keys and preferences for BeamNG.WorldForge
          </p>
        </div>

        {/* Save Message */}
        {saveMessage && (
          <div className={`mb-6 p-4 rounded-lg ${
            saveMessage.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
            {saveMessage.text}
          </div>
        )}

        {/* API Keys Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4">API Keys</h2>
          <p className="text-sm text-gray-600 mb-6">
            Configure API keys for external services. All keys are securely encrypted.
          </p>
          
          <div className="space-y-4">
            {renderAPIKeyField(
              'Sentinel Hub Client ID',
              'sentinel_hub_client_id',
              'sentinel_hub',
              'Free satellite imagery and DEM data (30,000 requests/month)',
              false
            )}
            
            {renderAPIKeyField(
              'Sentinel Hub Client Secret',
              'sentinel_hub_client_secret',
              'sentinel_hub',
              'Client secret for Sentinel Hub authentication',
              true
            )}
            
            {renderAPIKeyField(
              'OpenTopography API Key',
              'opentopography_api_key',
              'opentopography',
              'Free high-resolution DEM data worldwide',
              true
            )}
            
            {renderAPIKeyField(
              'Azure Maps Subscription Key',
              'azure_maps_subscription_key',
              'azure_maps',
              'Microsoft Azure Maps for satellite imagery',
              true
            )}
            
            {renderAPIKeyField(
              'Google Earth Engine Project ID',
              'gee_project_id',
              'gee',
              'Optional: For advanced Earth Engine features',
              false
            )}
          </div>
        </div>

        {/* Preferences Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Preferences</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Default Data Source
              </label>
              <select
                value={settings.preferences.default_data_source}
                onChange={(e) => handlePreferenceChange('default_data_source', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="opentopography">OpenTopography</option>
                <option value="sentinel_hub">Sentinel Hub</option>
                <option value="azure_maps">Azure Maps</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Default Image Source
              </label>
              <select
                value={settings.preferences.default_image_source}
                onChange={(e) => handlePreferenceChange('default_image_source', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="sentinel_hub">Sentinel Hub</option>
                <option value="azure_maps">Azure Maps</option>
                <option value="bing_maps">Bing Maps (Deprecated)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Language
              </label>
              <select
                value={settings.preferences.language}
                onChange={(e) => handlePreferenceChange('language', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="en">English</option>
                <option value="ru">Русский</option>
              </select>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end gap-4">
          <button
            onClick={loadSettings}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-semibold"
          >
            Reset
          </button>
          <button
            onClick={saveSettings}
            disabled={isSaving}
            className="px-6 py-3 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-400 font-semibold flex items-center gap-2"
          >
            <Save size={20} />
            {isSaving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>

        {/* Help Section */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-bold text-blue-900 mb-2">Need Help?</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• <a href="https://apps.sentinel-hub.com/" target="_blank" rel="noopener" className="underline">Get Sentinel Hub API keys</a></li>
            <li>• <a href="https://opentopography.org/" target="_blank" rel="noopener" className="underline">Get OpenTopography API key</a></li>
            <li>• <a href="https://azure.microsoft.com/en-us/products/azure-maps" target="_blank" rel="noopener" className="underline">Get Azure Maps subscription</a></li>
          </ul>
        </div>
      </div>
    </div>
  );
};
