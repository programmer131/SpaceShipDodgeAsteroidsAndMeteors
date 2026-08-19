using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

public enum GameState
{
    StartMenu,
    Playing,
    GameOver
}

public class GameManager : MonoBehaviour
{
    public const float SpawnFrequency = 0.4f;
    public const int MaxLives = 3;

    public AudioSource AudioSource;
    
    public Meteor Metoer1;
    public Meteor Metoer2;
    private float _elapsed;

    public TMP_Text _scoreUi;
    public TMP_Text _livesUi;
    public GameObject startButton;

    public GameState currentState = GameState.StartMenu;
    private int _lives = MaxLives;
    private float _score;
    private float _highscore;

    private float _timeScale = 1.0f;
    private float _gameOverTimer = 0f;

    private void Start()
    {
        currentState = GameState.StartMenu;
        if (startButton != null)
        {
            startButton.SetActive(true);
        }
    }

    public void StartGame()
    {
        currentState = GameState.Playing;
        _score = 0f;
        _lives = MaxLives;
        _elapsed = 0f;

        ClearAllMeteors();

        var player = FindObjectOfType<Player>();
        if (player != null)
        {
            player.transform.position = new Vector3(0f, -3.5f, 0f);
        }

        if (startButton != null)
        {
            startButton.SetActive(false);
        }
    }

    private void Update()
    {
        if (_timeScale < 1.0f)
        {
            _timeScale += Time.deltaTime * 0.5f;
            AudioSource.pitch = Time.timeScale = _timeScale;
        }
        else if (_timeScale > 1.0f)
        {
            AudioSource.pitch = Time.timeScale = _timeScale = 1f;
        }

        if (currentState == GameState.Playing)
        {
            _elapsed += Time.deltaTime;
            if (_elapsed >= SpawnFrequency)
            {
                _elapsed = 0f;

                var meteorToSpawn = Random.value > 0.5 ? Metoer1 : Metoer2;
                var meteor = Instantiate(meteorToSpawn);
                meteor.transform.position = new Vector3((Random.value * 16f) - 8f, 6f, 0f);
            }

            _score += Time.deltaTime;
            if (_highscore < _score)
                _highscore = _score;

            UpdateUI();
        }
        else if (currentState == GameState.GameOver)
        {
            _gameOverTimer -= Time.unscaledDeltaTime;
            if (_gameOverTimer <= 0f)
            {
                currentState = GameState.StartMenu;
                if (startButton != null)
                {
                    startButton.SetActive(true);
                }
            }
        }
    }

    private void UpdateUI()
    {
        if (_scoreUi != null)
        {
            _scoreUi.text = $"Score: {_score:F2}\r\nHighscore: {_highscore:F2}";
        }

        if (_livesUi != null)
        {
            _livesUi.text = $"Lives: {_lives}/{MaxLives}";
        }
    }

    public void Hit()
    {
        if (currentState != GameState.Playing)
            return;

        _lives--;
        AudioSource.pitch = Time.timeScale = _timeScale = 0.5f;

        if (_lives <= 0)
        {
            currentState = GameState.GameOver;
            _gameOverTimer = 5.0f;
            ClearAllMeteors();
        }
    }

    private void ClearAllMeteors()
    {
        var meteors = FindObjectsOfType<Meteor>();
        foreach (var meteor in meteors)
        {
            if (meteor != null)
            {
                Destroy(meteor.gameObject);
            }
        }
    }

    private void OnGUI()
    {
        GUIStyle titleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 32,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter
        };
        titleStyle.normal.textColor = Color.white;

        GUIStyle subtitleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 20,
            alignment = TextAnchor.MiddleCenter
        };
        subtitleStyle.normal.textColor = Color.yellow;

        GUIStyle buttonStyle = new GUIStyle(GUI.skin.button)
        {
            fontSize = 22,
            fontStyle = FontStyle.Bold
        };

        GUIStyle rightAlignStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 20,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.UpperRight
        };
        rightAlignStyle.normal.textColor = Color.cyan;

        if (currentState == GameState.StartMenu)
        {
            float w = 240;
            float h = 60;
            float x = (Screen.width - w) / 2;
            float y = (Screen.height - h) / 2;

            GUI.Box(new Rect(x - 20, y - 90, w + 40, h + 120), "");
            GUI.Label(new Rect(x - 100, y - 70, w + 200, 40), "SPACE DODGE", titleStyle);

            if (GUI.Button(new Rect(x, y, w, h), "START GAME", buttonStyle))
            {
                StartGame();
            }
        }
        else if (currentState == GameState.Playing)
        {
            if (_livesUi == null)
            {
                GUI.Label(new Rect(Screen.width - 210, 10, 200, 40), $"Lives: {_lives}/{MaxLives}", rightAlignStyle);
            }
        }
        else if (currentState == GameState.GameOver)
        {
            float w = 340;
            float h = 180;
            float x = (Screen.width - w) / 2;
            float y = (Screen.height - h) / 2;

            GUI.Box(new Rect(x, y, w, h), "");
            GUI.Label(new Rect(x, y + 15, w, 40), "GAME OVER", titleStyle);
            GUI.Label(new Rect(x, y + 60, w, 30), $"Total Score: {_score:F2}", subtitleStyle);
            GUI.Label(new Rect(x, y + 90, w, 30), $"High Score: {_highscore:F2}", subtitleStyle);
            GUI.Label(new Rect(x, y + 130, w, 30), $"Restarting in {Mathf.CeilToInt(_gameOverTimer)}s...", subtitleStyle);
        }
    }
}

